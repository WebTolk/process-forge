# ProcessForge architecture decisions

[Русская версия](../ru/architecture/README.md)

Use this register with the source revision you are designing against or reviewing.
The identifiers come from the October 2026 architecture review. Each entry
records a design boundary and links to its public contract where available.
The [November reconciliation](../audits/architecture-decisions-20261118.md)
records later changes and open findings against a fixed revision.

## Product and Work

- **D01 — Local, domain-neutral Core.** ProcessForge supports file-first local
  work and library use. Garage can work without Runtime, MCP, a network or an
  LLM. SQLite owns selected operational facts. Work definitions, capsules and
  substantive artifacts use files. [Core boundary](../concepts/domain-neutral-core.md),
  [execution storage](../concepts/execution-storage.md)
- **D02 — Pinned Work.** Run and assignment identity, the process definition and
  the context capsule are pinned. The process owns transition selection.
  Effective authorization limits reads and resource references remain portable.
  [Context capsule](../concepts/context-capsule.md),
  [Work context](../concepts/work-context.md)
- **D03 — Prepared execution and authorization.** Work and executor contracts
  are driver-neutral. Empty grants deny resource access. A `metadata_only` grant
  permits only metadata reads. Prepared execution stays within its assigned Work and
  the host defines actual OS isolation. Required journal facts and evidence are
  separate from optional diagnostics. In the revised MCP contract, worker declarations
  record requested servers and the coding agent owns connections and approvals.
  [Work execution](../concepts/work-execution-contract.md),
  [worker resource contract](../concepts/work-context.md)
- **D04 — Agent entry.** The root `AGENTS.md` is a short portable entry point.
  Load specialized instructions when they apply. Resource authority comes from
  the applicable policy and context. The historical `START` file is optional.
  Verify instruction delivery and the resulting agent behavior separately.
  [Agent entry](../concepts/agent-entry.md)

## Core ownership and execution

- **D05 — Configuration service.** Keep PFConfig independent of CLI, MCP and
  process environment. Separate the model, service, storage adapter and
  transport. Apply defaults for absent values and keep reads free of state
  creation. D18 specifies the merged configuration boundary.
- **D07 — Refactoring scope.** Move existing behavior into cohesive Core
  services. Preserve published behavior and interfaces under the project's
  compatibility policy. New subsystems and public APIs require a separate
  design decision. [Core structure](../concepts/python-core-structure.md),
  [compatibility policy](../../CONTRIBUTING.md#storage-readiness-and-mandatory-migration)
- **D08 — Direction of calls.** The CLI, MCP and remaining procedural code call
  the Core service that owns the operation. An extracted service still using a
  callback into the monolith for its business rules is an incomplete extraction.
  Explicit infrastructure ports are permitted. [Core structure](../concepts/python-core-structure.md)
- **D10 — Core identity.** Use a shared CoreProperties contract for build-aware
  callers. Report the loaded and installed builds separately. Product,
  component, protocol and schema versions have separate meanings.
  [Runtime monitor](../concepts/runtime-monitor.md)
- **D11 — Current execution and history.** Keep physical execution state,
  execution history and result collection distinct. Checking current activity
  must remain bounded with 400,000 historical launches. That number is an
  acceptance criterion. [Execution storage](../concepts/execution-storage.md)
- **D19 — Owned execution and short leases.** Establish ownership and exclusion
  at the operation that needs them. In the native design, the loaded image is
  scoped to its process and short leases to operations. Idle MCP or Runtime
  processes release those leases. A publication seal checks consistency under
  trusted bootstrap and archive assumptions. Arbitrary historical writers must
  be addressed explicitly during maintenance. See the
  [revised migration boundary](../audits/architecture-decisions-20261118.md).
- **D22 — Managed egress.** Apply strict managed-egress guarantees to the
  mediated, policy-bound protocol and its qualified providers. Shell workers and
  native agent CLIs retain their own declared isolation and capability boundaries.
  [Egress engine](../concepts/egress-engine.md)

## Storage and configuration

- **D09 — Event journals.** Project events and raw hook records use SQLite.
  Preserve admission, pending-delivery and verification facts independently of
  optional history. Garage hooks are opt-in. Forge retains the checks required
  for its coordination mode. [Hook journals](../concepts/hook-journal-sqlite.md)
- **D12 — Usage accounting.** Keep local PF usage in a shared accounting store
  keyed by stable project identity. Runtime and usage statistics have a distinct
  boundary from financial functions. [Usage accounting](../concepts/usage-accounting.md)
- **D13 — Search maintenance.** Context, initialization, repair and queries
  use the available index and return promptly when it is unavailable. Starting,
  scheduling and waiting for a build belong to explicit index maintenance through Core.
  SQLite FTS5 is the default. The October design deferred RAG, additional
  backends and a shared scheduler.
  [Search index](../concepts/resource-search-index.md)
- **D14 — Storage topology.** The target has a primary Workplace store, a
  primary store per project and a separate derived Search index. The project
  owns its canonical Work and execution data. Workplace views use summaries and
  references. Existing journal owners and paths remain explicit at cutover.
  [Execution storage](../concepts/execution-storage.md)
- **D15 — R02 execution authority.** Use the synchronous SQL interface for
  Project execution current state and history. Reserve an attempt before
  spawning it and switch authority to the validated target durably. Work YAML
  and capsules stay file-owned. Treat migration of existing stores as an
  explicit operation. [Execution storage](../concepts/execution-storage.md)
- **D16 — SQLite default.** SQLite is the default storage driver in PFConfig
  with a supported project override boundary. Wrapping an already supported
  SQLite path alone requires no data movement. Driver selection and readiness
  for an ordinary write are separate checks. The October design used one driver.
  [Execution storage](../concepts/execution-storage.md)
- **D17 — Journal migration.** Preserve store UUIDs, source data, necessary
  metadata and a recoverable checkpoint. New projects start with SQL journals.
  Explicit migration must precede ordinary writes to historical stores. The
  enrolled project event journal can be migrated under a compatible active
  Runtime with project-owned admission and a durable pending pin. Offline
  maintenance covers shared and other historical stores and unmanaged writers.
  [Project event migration](../concepts/execution-storage.md#migrate-one-project-event-journal-with-runtime-online).
- **D18 — Full merged PFConfig.** All components consume the effective
  configuration. Keep the presence-aware merge across builtin, device,
  Workplace, project and context settings, including allowed and locked keys.
  Pin an immutable snapshot to each operation and worker so that a selection
  from one project cannot leak into another.
  [Runtime configuration](../concepts/runtime-configuration.md)

## Historical decisions

- **D06 — Framework proposal.** The October 5 proposal is historical. D07 and
  D08 govern scope and service ownership. The proposed Kernel, DI and provider
  structure remained a proposal beyond those accepted boundaries.
- **D20 — First cold transition.** The October design allowed one cold handoff
  for historical installations without a proven owner. The November decision
  replaces the historical manager and cold-controller route with explicit
  offline migration. [Journal maintenance](../concepts/sqlite-journal-maintenance.md),
  [reconciliation](../audits/architecture-decisions-20261118.md)
- **D21 — Alpha6 checkpoint.** The instruction to finish the combined alpha6
  and stop applied to that delivery stage. Full 1.2-to-1.3 upgrade qualification
  belonged to a later stage. Continue to record source, archive,
  installed Core, Runtime and actual connected-client evidence separately.
  [Release checklist](../release-checklist.md)
- **H01 — Prerelease compatibility exception.** The original exception applied
  before public users relied on the product. Public contracts follow the current
  SemVer and migration policy. [Compatibility policy](../../CONTRIBUTING.md#storage-readiness-and-mandatory-migration)
