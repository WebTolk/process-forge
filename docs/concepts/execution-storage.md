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
| Capsules, prepared inputs, substantive artifacts | Immutable files |
| Interpreted execution facts after explicit cutover | Project SQL |
| Process/heartbeat/exit receipts | Evidence admitted by exact launch identity |
| `status.json` after cutover | Generated compatibility projection |
| Ledger session ownership | Existing Agent Ledger |

Legacy events, hooks and accounting keep their existing stores and identifiers.
Search remains a separate derived database. The future workplace main store is
not activated by this slice. This is transitional storage topology.

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

## Routing and recovery

Before opt-in, an unbound project retains the existing legacy route. Reads and
construction create nothing. An existing bound project must verify exact
project/store identity, namespace and SQL readiness; a missing, corrupt, foreign
or partial target blocks without falling back to JSON. Binding pins routing;
the SQL transaction alone establishes authority/readiness. Explicit project ID
is required; a directory-name fallback cannot authorize initialization/migration.

Migration requires explicit offline maintenance, exclusion of old writers, proven
quiescence, stable sources, verified backup and checkpointed import. No live
process takeover is supported. A pending binding blocks capable writers. History
may be incomplete while active coverage must be complete for first cutover.
After cutover, recovery rolls forward from SQL and repairs derived projections;
JSON is never reimported as new truth. Old binaries cannot be technically fenced
by a marker they do not understand and are unsupported writers after cutover.
Only explicit successful new-project initialization may choose the fresh SQL
route; existing roots, including forced initialization, are not fresh by inference.
