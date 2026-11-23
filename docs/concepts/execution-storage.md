# Execution storage and authority

The execution domain provides immutable DTOs in `processforge_core.executions.model`
and the synchronous `ExecutionRepository` protocol in `executions.ports`.
Importing or constructing them performs no I/O and initializes no backend.
Repository, service, OS observation, migration and adapter composition are separate
layers. This document defines their authority boundary; the DTO slice alone does
not enable SQL routing or prove integrated runtime acceptance.

## Semantic versioning and required migration

Development strictly follows [Semantic Versioning 2.0.0](https://semver.org/) and
the [lasting contributor rules](../../CONTRIBUTING.md#storage-readiness-and-mandatory-migration).
Compatibility concerns the published contracts experienced by users and their
agents: supported workflows, public interfaces, integrations, and data/identity
guarantees. Incompatible public changes require MAJOR, compatible functionality
MINOR, and compatible bug fixes PATCH. The policy is not tied to a fixed release.
Unreleased intermediate implementations and tests do not add public contracts.

A small supported project migration does not itself require MAJOR. Internal
storage formats may change through an explicit migration using the provided tools
while preserving those user-facing contracts without reworking integrations.
Document and verify migration and recovery. A migration tool does not make a
broken public contract compatible.

New projects initialize current journals/stores directly. Existing projects must
complete the applicable qualified migration before ordinary writes resume.
Preserve released data and identity guarantees; do not keep an ordinary
legacy-write fallback to avoid migration. Missing readiness or safety evidence
means refusal, not a successful upgrade.

## Identity and validation

`ExecutionKey(project_id, run_id, task_id, attempt)` identifies an existing
assignment attempt. `task_id` is the assignment ID, not another entity. Nonblank,
NUL-free UTF-8 identifiers are preserved exactly: no lowercasing, trimming,
Unicode normalization, path-based IDs or replacement IDs. Callers retain existing
selector/path validation. Attempt is an exact integer at least 1; bool is refused.

All DTOs are frozen dataclasses. Revision starts at 1, generation at 0;
`projected_revision` is between 0 and record revision. Process identity carries
host, optional boot, positive PID, opaque birth identity and optional owned-tree
identity. These shapes never prove that a process exists or that its tree is gone.

Payload text must be a JSON object without duplicate keys, nonfinite values,
NUL or invalid UTF-8 strings. The model preserves exact text and unknown fields.
Adapters validate the compatibility schema and canonicalize transaction payloads
using sorted keys, compact separators, UTF-8, `ensure_ascii=False`,
`allow_nan=False`. Model construction does not authenticate a receipt or verify
its checksum against unavailable original evidence. Observation timestamps require
an explicit UTC offset; launch/store identities use UUID hex and checksums use
`sha256:` followed by 64 lowercase hex digits.

## Independent owners

| Facts | Authority |
| --- | --- |
| Run and assignment stages | Existing Work YAML |
| Canonical knowledge and file resources | Existing files |
| Capsules, prepared inputs, substantive artifacts | Immutable files |
| Interpreted execution facts after committed SQL cutover | Project SQL |
| Process/heartbeat/exit receipts | Evidence admitted by exact launch identity |
| `status.json` after cutover | Generated compatibility projection |
| Ledger session ownership | Existing Agent Ledger |

Legacy events, hooks, accounting and search retain their recognized paths,
domain application IDs, domain versions and data. Search remains a separate
derived database. Additive UUID adoption in recognized legacy stores is distinct
from the PF main envelope and execution JSON import: it does not move domain rows
or activate SQL execution authority. The future workplace main store is not
activated. This remains transitional topology; other drivers, RAG, scheduler and
full legacy-domain consolidation are outside this contract.

`pf_store_meta` retains UUID/scope/stable owner identity; `pf_schema_versions`
retains code-owned namespaces, versions and checksums. Legacy adoption registers
only `store_identity@1` while preserving qualified domain schemas, constraints
and FTS objects. Main uses its own envelope with `execution@1` and
`execution_migration@1`. Legacy identity pins and the execution binding pin exact
targets; execution main has no duplicate legacy identity pin. UUID metadata alone
does not grant access or replace domain validation. Foreign, corrupt, future,
drifting or conflicting stores are refused without relabeling or rebuild fallback.

## Configuration and immutable snapshots

One native, context-bound `ConfigurationProvider` supplies the full application
`PFConfig` to CLI, standalone Core, MCP/Runtime/hooks, workers and maintenance.
For permitted keys the order is builtin -> device -> explicitly stored fields
of the selected workplace -> project -> authorized context. Presence comes from
the same validated YAML read; explicit false or default-valued fields still
override, and absent workplace keys inherit device values. Project/context use
the typed `ProjectPFConfig` allowlist and null-inherit semantics. They cannot
override locked policy or fields outside that allowlist. Configuration grants no
filesystem, SQL, infrastructure or model-visible body access.

The device source contains full PFConfig, not a driver-only global reader.
`database.driver` follows the same merge; SQLite is the operational default when
no selector is set and the only implemented driver. Missing configuration requires
no new file or serialized `database` section. Profiles remain a separate validated
target mechanism: collisions and scope violations refuse; configuration refresh
cannot hot-switch a bound store UUID/path. The declared device path is selected
once for the command/session without disk scan or CWD discovery. See
[Runtime configuration](runtime-configuration.md) for provider and CRUD details.

The host takes one explicit snapshot per operation and passes a pinned provider
downstream. Refresh affects subsequent operations, never an existing snapshot;
there is no mutable global current-project configuration. Cold construction does
no reads or initialization. Pure reads create no configuration, DB or maintenance
files. Invalid initial input errors; later invalid reload retains last-valid
source and presence together with diagnostics under the existing rules.

New native launches carry a private attempt-local `configuration.snapshot.json`,
pinned before spawn and checked for exact authorized path, hash, attempt identity,
size <= 65536 bytes and strict PFConfig shape. The wrapper passes the same pointer/hash to its
child; it does not reread live configuration mid-attempt. This sidecar is not
policy, a prompt input, a public status field or a capsule mutation. Its native
scope must be explicitly granted; missing authority refuses the dependent launch.
Existing running legacy wrappers retain their legacy route. A standalone wrapper
without pinned transport may use the provider only with its own authorized read
scope. Metadata-only visibility never authorizes reading a body.

## Physical activity, outcome and collection

Internal phases are `prepared`, `starting`, `running`, `stopping`, `unresolved`,
`absent`. Only starting/running/stopping/unresolved belong in current snapshots.
A prepared attempt has no current row. Reservation commits before process creation;
controller death leaves ownership unresolved without TTL reclamation. A stop
request or successful signal does not prove absence. PID reuse, denied inspection,
unproved descendants or missing evidence keep activity unknown.

Proven full-tree absence pairs an outcome with a monotonic history sequence and
removes current ownership atomically. Internal outcomes are completed, failed,
timed_out, cancelled, unknown_exit, lost and blocked. They do not introduce public
status enum values. In particular, `unknown_exit` needs mapping into an existing
adapter status. Public payload schema remains version 1; launch token, revision
and generation are private facts, not new public status fields.

Collection is independently pending, collected, failed or refused. A collection
failure does not revive a process; semantic refusal never means accepted output.
Later receipts and collection do not reorder history. Evidence for an old attempt
may update only its exact key, never the latest attempt by inference.

## Repository and read guarantees

Mutations compare generation and expected revision. Receipts are admitted by exact
key, launch token, kind, sequence and checksum: identical admitted evidence is a
no-op, conflicting same-sequence content refuses, lower sequence is stale no-op.
Attached process birth identity cannot change. Domain ports expose no SQL session,
CLI object or filesystem path. No transaction spans spawning, signals, waiting,
output reads, backup, scans or projection I/O.

`current(limit=128, deadline=None)` reads readiness and only indexed current rows in
one snapshot. Limits are 1..1000. Overflow, unknown coverage, missing/unsupported
storage or deadline exhaustion must never turn an incomplete empty result into
proof of zero activity. Deadlines are absolute monotonic times. The guard does no
history scan, terminal receipt read, reconciliation or signaling. History pages
use monotonic sequence order and a captured high water, default limit 256.
`after=None` denotes no further page. Projection acknowledgment is a latest-key/
revision/generation CAS that does not increment lifecycle revision.

SQL heads/current/history sequence, launch tokens, process identity, receipt
admissions and projection acknowledgments remain separate facts with distinct
roles. Under the existing task lifecycle lock, projection publishes the latest
authoritative compatibility DTO by atomic `status.json` replacement, then CAS
acknowledgment. Failure leaves the head dirty for indexed/exact-task repair;
an older attempt cannot overwrite the latest projection. CLI/MCP/continuation
read SQL after cutover even when that projection is stale.

## Admission and bounded observation

Capable spawn paths acquire workplace admission when enrolled, then project
admission, the existing task lifecycle lock and finally a SQL transaction.
Reservation commits before spawn; no SQL transaction spans process creation.
Shutdown and registration use the same admission protocol and durable Runtime
stopping fence. Unknown routing, ownership, tree state or gate timeout preserves
unknown activity; TTL and PID-only probes never prove idle. An enrolled project
cannot bypass an unavailable workplace gate by claiming standalone status.
The 500 ms guard only observes bounded current state: no migration, backup or
history scan. The 400,000-history zero-terminal-read acceptance concerns SQL-ready
operation; legacy projects retain their existing bounded observer semantics.
File-only operation requires no Runtime/MCP bootstrap, network or LLM.

## Migrate one project event journal with Runtime online

Use `--project-events` for an existing SQLite event journal in an enrolled
project. Pass the project and its actual Workplace. The Runtime must advertise
the `project_event_maintenance` capability. Any unmanaged writers to the
selected journal must be stopped before applying.

```text
python -B tools/migrate-storage.py --project-root PROJECT --workplace-root WORKPLACE --project-events --inspect --json
python -B tools/migrate-storage.py --project-root PROJECT --workplace-root WORKPLACE --project-events --apply --json
python -B tools/migrate-storage.py --project-root PROJECT --workplace-root WORKPLACE --project-events --resume --json
```

The migrator reports the selected target. It admits the operation for that
project, waits for its managed storage accesses to finish, and retains a
verified backup and the exact migration plan. While the journal is fenced,
the selected project can receive `storage_project_event_maintenance_busy`
or `storage_resume_required`. A competing migration returns a retryable
busy result. Other enrolled projects keep using the same Runtime for Work,
events and hook delivery.

After interruption, retry `--resume` with the same roots and configuration.
The pending identity pin fences ordinary access until verification succeeds.
For recovery with Runtime stopped, add `--offline-confirmed` to the same
selected command after stopping all writers to that journal. Use `--inspect`
to confirm `ready`, then refresh the project's context. The offline procedure
below covers shared Workplace stores, execution storage and older NDJSON imports.

## Explicit migration and update responsibility

New projects use SQL immediately. Existing projects with legacy journals refuse
ordinary Work/worker writes with `storage_migration_required` until the operator
runs the supported migration. Read-only status/config/doctor operations do not
migrate. Core file replacement does not migrate every project automatically.

In Garage the operator stops PF and all writers before maintenance. In Forge the
updater stops the single PF executor before replacing files and restarts it after
maintenance. PF does not claim technical exclusion of arbitrary historical
processes. No historical manager, enrollment, cold controller or release-specific
authority transfer is required.

With PF stopped, inspect and import event/raw journals, then bind existing stores
and import execution snapshots:

```text
python -B bin/pf.py journal-maintenance inspect --project-root PROJECT --workplace WORKPLACE --json
python -B bin/pf.py journal-maintenance import --project-root PROJECT --workplace WORKPLACE --apply --json
python -B tools/migrate-storage.py --project-root PROJECT --workplace-root WORKPLACE --apply --offline-confirmed --json
```

`--offline-confirmed` records operator/updater responsibility. The host also
requires the actual project/workplace admission lock, rejects a known live
Runtime, pins current configuration, roots, owners and targets, and rechecks that
selection before mutation. Confirmation does not bypass source, identity, schema,
backup or checkpoint validation. Unsupported or changed inputs remain blocked.

The pending binding precedes DB mutation. Ready access verifies the store UUID,
owner, path, schema and readiness. An existing missing/partial bound store never
falls back to JSON or gets a new identity. Execution import preserves observable
snapshots and allocation floors; it does not invent overwritten history. Batches
and checkpoints commit together. The SQL CAS from importing/legacy to ready/sql
is the execution cutover; adding UUID metadata alone is not that commit.

Migration retains frozen sources, transform hashes, verified WAL-aware backups,
journals and checkpoints. Resume explicitly with the same roots and
`--resume --offline-confirmed`. It must match the original plan, sources and
backup; it does not remint UUIDs or overwrite recovery evidence. An already-ready
store is not rolled back when another target fails. After SQL writes, old-Core
rollback is not data rollback and JSON must not be reimported as new truth.

Fresh project authority comes from exclusive creation of its flow root and the
receipt at `maintenance/project-initialization.json`. It is independent of the
ability to launch native workers. Main SQL and events storage are ready before
the first onboarding event; project raw/search stores retain planned UUIDs and
initialize lazily. Recovery reuses the receipt, physical root, owner, routing and
UUIDs. A foreign, missing-ready or corrupt store refuses recreation.

Existing native worker ownership and short cooperating OS leases remain in use
for their own lifecycle. They do not certify unknown old processes or authorize
migration. Ordinary reads and writes cannot turn a legacy project into a fresh
one. See [journal maintenance and recovery](sqlite-journal-maintenance.md).
