# Continue existing Work

Use continuation when the intent is to resume existing work. Rewording an objective in `work-start` is not a Work selector: legacy matching only normalizes case and whitespace. Continuation never creates a Run, assignment or execution capsule and never grants additional access.

1. Read current `pf.context`. Use `pf.continuation.status` without an id to discover candidates. Discovery is bounded and never chooses the newest record for you; multiple candidates return `choice_required`, none returns `not_found`.
2. Select the exact run, assignment and context. `pf.continuation.create` takes `continuation_id`, `run_id`, `assignment_id`, `context_id`, optional `expected_artifacts`, `handoff_id`, `instruction`, and `apply`. Preview is the default; `apply: true` persists a v2 reference with the capsule checksum.
3. `pf.continuation.status` with the id reports waiting readiness separately from Work readiness. A handoff must be returned/finalized and expected files must exist inside the project. Work verification checks the pinned identity, source integrity, permissions, current context/stage and selected resources.
4. `pf.continuation.resume` verifies again under the Run lock and returns `selectors` and `work_state`. A bound session receives a durable session-specific selection. Without a stable session id, `selection: explicit_selectors_required` requires passing the returned run/assignment/context ids to subsequent `pf.work.state` and `pf.work.transition`. There is no project-global sessionless selection.

The CLI offers the same operations:

```text
pf continuation-status --project-root . --json
pf continuation-create --project-root . --id resume-feature --run feature-run --assignment feature-task --context-id feature-task-capsule --apply --json
pf continuation-resume --project-root . --continuation resume-feature --json
pf work-state --project-root . --run feature-run --assignment feature-task --context-id feature-task-capsule --json
```

Creation never overwrites a different continuation intent. Resuming is idempotent. Invalid/terminal selected Work or an active worker/lease blocks without falling back to a newer task. A newer backlog entry cannot displace a session's explicit selection. A session selection receipt is committed before the derived `resumed` marker; repeating resume repairs an interrupted marker write after revalidation. The partial result is explicit: `selection_committed`, `marker_recovery_required: true`. It does not repeat a stage transition.

Version 1 records retain their wait-only behavior, explicitly reporting `work_resumed: false` and `legacy_binding_required`. They are not silently upgraded: create a new exact v2 reference. Merely marking a legacy wait resumed is not proof of Work resumption. No-scope legacy Work creation remains compatible, but `work_state.execution_readiness` reports missing effective permissions; such records cannot be resumed for execution. Explicit read-only Work is supported.

## Cancel one Work

`pf.work.cancel` / `pf work-cancel` requires exact run, assignment, context, capsule checksum and reason; evidence paths are optional and must reference existing bounded project files. Preview is the default; apply must be explicit. It cancels only the addressed assignment. A multi-assignment Run remains active while other members are active.

Cancellation checks worker state and leases, serializes with worker lifecycle and Run changes, and never kills a process or revokes a lease. A durable checksummed intent makes partial persistence recoverable by retrying the same request. Normal transitions are blocked while cancellation recovery is pending. Concurrent unexpected changes stop replay. Events use stable ids; capsule, process pin and stage history remain unchanged. Cancellation is not completion, deletion, rollback, or permission to start a successor.

Source support, archive verification, installed Core and actual connected host acceptance are separate levels. Adding these commands in source does not reload an existing MCP host.
