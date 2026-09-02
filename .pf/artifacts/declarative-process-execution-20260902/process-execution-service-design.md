# Process Execution Service Design

Status: ready_for_review
Date: 2026-09-02

## Ownership

`ProcessExecutionService` is the only high-level owner of declarative process
execution. It depends on filesystem and ProcessForge primitives injected as
`core`; it has no MCP, CLI, Codex, Joomla, process-id, or platform knowledge.

Public operations:

- `start(objective, session_id="")`
- `state(run_id="", assignment_id="", session_id="")`
- `allowed_transitions(...)`
- `transition(outcome, evidence, notes, ...)`
- `can_complete(...)`
- `complete(...)`

## Canonical state

Run and Assignment YAML are canonical. A new Run pins:

- Process id and version;
- canonical Process fingerprint;
- full normalized effective Process definition;
- context snapshot id and checksum;
- immutable Assignment capsule path and checksum.

`Assignment.stage` is the current effective stage. `stage_history` records
completed/blocked transitions and evidence. The NDJSON event journal is the
durable event history. JSON projections are derived and replaceable.

## Consistency

Mutations acquire the existing per-path registry lock for the Run. Run,
Assignment, capsule, summary, handoff, and execution projection writes use
same-directory temporary files followed by atomic replacement. Events are
appended only after canonical state commits.

## Compatibility

Existing low-level Run/Task commands remain available. Existing unpinned runs
are readable as `legacy_unpinned`; declarative transitions require a pinned
definition so Process YAML cannot silently change during a Run.

Garage start delegates to the service. MCP and CLI translate arguments and
results only. Runtime-host work state may reuse service state while retaining
its existing diagnostic envelope.
