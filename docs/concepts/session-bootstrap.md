# Session Bootstrap

> Advanced Forge/operator interface. Ordinary Garage work uses `pf.context`,
> optional `pf.search`/`pf.resolve`, and `pf.work.start`, then `pf.work.state`
> and `pf.work.transition` until `run_completed`. It does not require manual
> session creation or starting the onboarding placeholder assignment.

## Ordinary Entry Order

1. Load root `AGENTS.md` through the selected client route. For an unmigrated
   legacy project without it, explicitly read `.pf/AGENTS.md`.
2. Read `.pf/process-forge.yaml` and verify current context with `pf.context`.
   If MCP is unavailable, use the existing CLI `project-context-check` and its
   verified context fallback; a snapshot's presence alone is not freshness proof.
3. Use `pf.search` and `pf.resolve` for relevant authorized resources. Start or
   reuse governed work with `pf.work.start`. Handle `process_choice_required`
   using the returned choices; do not guess a default process.
4. Use the returned Run, assignment and immutable capsule identities throughout
   `pf.work.state` and `pf.work.transition`. Read their required sources and
   relevant handoffs; do not select an unrelated assignment from an old report.
5. Read extended `.pf/AGENTS.md` instructions and other resources on demand.

Global instructions remain applicable, but a global navigation hint is not proof
that K reached the client. Optional `agent-start-prompt` prints current guidance
without writing files or treating stored START as authority. See
[agent entry](agent-entry.md) and [global sections](global-agent-section.md).

## Explicit session commands

`session-start --agent` uses the Ledger check-in path. With `--mode`, the CLI
requires an existing project flow root. It checks the snapshot, records the
selected mode, writes private session metadata and telemetry, and emits
project events. A supplied `--assignment` contributes an assignment reference
and a start event. `--allow-write` permits the session status report unless
`--report-only` is also set. An explicit `--rebuild-context-if-stale` can
refresh a missing or stale snapshot.

The mode labels include `resume`, `project_init`, `assignment_execute`,
`context_resolve`, `context_compile` and `doctor_context`. To create a project
use [project onboarding](../getting-started/project-onboarding.md). To launch
a worker use the [worker lifecycle](action-discovery.md). The session command
records the mode supplied by the caller.

## Rules

- Prefer verified fresh context over broad recomputation. Report stale, broken,
  denied-resource or missing-capability conditions; refresh only when authorized.
- Machine-readable assignment and pinned capsule define execution boundaries;
  Markdown reports are supporting context and cannot override live state.
- Explicit session operations write private metadata/telemetry under
  `.pf/runtime/` and events under `.pf/runtime/events/`.
- Ordinary work must not install, start or repair Runtime, MCP, hooks or Ledger.
  Report infrastructure blockers to the operator.

The CLI can run this bootstrap locally. Project events use the [SQLite journal](hook-journal-sqlite.md).
