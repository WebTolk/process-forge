# Execution storage and authority

The execution domain provides immutable DTOs in `processforge_core.executions.model`
and the synchronous `ExecutionRepository` protocol in `executions.ports`.
Importing or constructing them performs no I/O and initializes no backend.
Repository, service, OS observation, migration and adapter composition are separate
layers. This document defines their authority boundary; the DTO slice alone does
not enable SQL routing or prove integrated runtime acceptance.

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

## Routing and native migration recovery

This page describes the accepted final contract. It does not assert that the
current live project has migrated or that integrated implementation QA has passed.

Ordinary supported updates and first safe writes invoke the native migration
script/service automatically, without project opt-in, manual data transfer or
agent/LLM/model-provider calls. `tools/migrate-storage.py` is the native inspection,
apply and recovery entrypoint; update invokes qualified installed code, while
first-write uses the same coordinator for standalone/file-only operation.
Installation success alone does not establish project readiness. Pure
status/config/doctor/guard reads do not initiate migration or scans.

Before any pending pin/binding, recognized unbound legacy projects retain their
existing route. Active or unknown ownership defers migration with diagnostics;
existing supported start/stop/collect behavior and active attempt IDs/receipts
remain intact. Retry occurs after terminal reconciliation/collection or on the
next mutating use, after lifecycle/target locks and SQL sessions are released.
There is no scheduler, polling loop, live takeover or automatic kill. A missing
explicit stable project/owner identity, ambiguous source or unknown old writer
cannot be turned into a safe window by configuration or an opt-in flag.

Proven safety is host evidence bound to the exact authorized project/store,
target and generation: quiescence, no pre-spawn gap or live owned tree, stable
sources and qualified exclusion of old writers. It is revalidated under admission
at freeze, resume and immediately before cutover. An empty registry, current
version, terminal string, elapsed TTL, PID probe or `offline_confirmed` alone is
not proof. Missing, stale, changed or unavailable proof prevents migration/cutover;
before pending the recognized legacy route above remains. Old binaries
cannot be technically fenced by markers they do not understand; they must be
excluded by actual ownership/maintenance evidence, and are unsupported writers
after SQL cutover.

When safety is proven, publish the exact pending identity pin/execution binding
before DB mutation. Capable clients then block ordinary access to the pending
target and permit only recovery of that exact plan. Missing/partial bound storage
never falls back to JSON or another target. Ready access verifies exact
project/store UUID, scope/owner, pinned path, schema/checksum and readiness.
Binding routes and pins identity; the SQL transaction alone sets execution
authority/readiness. Explicit manifest project ID is required; directory-name
fallback or silently minted replacement owner identity is forbidden.

Migration retains deterministic descriptors, frozen source manifests/original
bytes, verified WAL-aware backups, journals and same-batch checkpoints. UUID
adoption adds metadata in place without altering domain rows/IDs; its per-target
commit is separate from execution import and from the global file journal.
Unused absent stores are not created merely for abstraction. Execution import
uses observable latest snapshots only, no invented overwritten history; attempt
directory names only establish allocation floors. Import batches are at most
256, with import and checkpoint in one transaction. History may be incomplete,
but first cutover requires zero proven current executions and complete active
coverage. Invalid records cannot be skipped to conceal unknown active work.

The only execution cutover is the CAS commit of `execution_state` from
importing/legacy to ready/sql at the target generation together with the ready
`execution_migrations` marker. UUID adoption alone is not this commit. Before
the initiating write continues, a proven-safe migration completes synchronously;
interruption retains pending/checkpoint state for automatic exact resume on the
next mutating use. Resume verifies code/descriptor/source facts, the same backup
and checkpoint, without reminting UUIDs or creating an arbitrary second backup.
An already-ready target is not implicitly rolled back if a later target fails.

After cutover, recovery rolls forward from SQL and repairs only owned projections
and reports; JSON is never reimported as new truth. There is no automatic abort.
Explicit pre-cutover abort requires admission, unchanged sources and proof of no
ready authority/new SQL commits. Restore uses a new target and controlled offline
binding switch; old-Core rollback after SQL writes requires separately qualified
reverse export. Maintenance inspection and existing `journal-maintenance`
execution inspection/import/resume interfaces support diagnosis and controlled
repair; they are not ordinary user migration prerequisites. See
[SQLite journal maintenance](sqlite-journal-maintenance.md).

Only successful explicit initialization creating a new flow root may choose the
fresh SQL route. Existing roots, including forced initialization, are not fresh
by inference. Fresh binding/DB publication is recoverable rather than atomic
across files and SQL; a pending publication failure requires explicit repair.

The host now composes `build_storage_migration_host` without reading configuration,
connecting, taking gates or minting UUIDs. Its first operation resolves the exact
selected roots, stable owner IDs and main profile alias. An unqualified legacy
target defers before constructing its execution engine; a pending/bound target
cannot use that legacy route. Workplace stores without a stable owner produce
an explicit per-target diagnostic rather than a directory-derived identity.

Fresh initialization probes real suspended process creation and retained Windows
Job attachment from a qualified captured publication. SQLite configuration alone
does not select SQL execution. New-flow creation and initialization hold admission;
the exact binding precedes DDL. The private initialization marker permits explicit
repair with the same UUID/profile after interruption. Existing roots and forced
initialization do not acquire fresh authority.

The durable fresh-initialization marker closes legacy routing as soon as its
pending state is published, including interruption before the binding exists.
Reads report the pending route without repairing it. A safe ordinary mutation
or native resume can repair only the marker's exact owner, UUID and profile under
admission, qualified native capability and stable safety generation. Ready
publication revalidates safety; no alternate target or UUID is selected.
