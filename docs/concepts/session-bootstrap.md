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

## Explicit Session Request

Operator session bootstrap turns a structured request into a formal session.
The request has a session id, mode, actor, role, project root, optional
assignment path, and options for writes, cache use and context refresh. Its
schema and template remain `schemas/session-start.schema.json` and
`templates/session-start-template.yaml`.

## Modes

`resume` inspects existing project flow. By default it reports without changing
public artifacts while recording private session telemetry.

`project_init` starts Project Init. Applied initialization creates `.pf/` state
and full K in root and hidden AGENTS, subject to entry ownership/budget checks.

`assignment_execute` starts a bounded worker with its assignment and Execution
Context Package or snapshot-based capsule. It must respect those boundaries
rather than rediscovering the whole project.

`context_resolve` and `context_compile` are deprecated compatibility modes that
write into `.pf/contexts/`. Run/Task/session APIs remain available for explicit
compatibility and operator uses; they are not an ordinary-work fallback.

## Rules

- Prefer verified fresh context over broad recomputation. Report stale, broken,
  denied-resource or missing-capability conditions; refresh only when authorized.
- Machine-readable assignment and pinned capsule define execution boundaries;
  Markdown reports are supporting context and cannot override live state.
- Explicit session operations write private metadata/telemetry under
  `.pf/runtime/` and events under `.pf/runtime/events/`.
- Ordinary work must not install, start or repair Runtime, MCP, hooks or Ledger.
  Report infrastructure blockers to the operator.

The file-only bootstrap needs no backend, database, dashboard or mandatory runner.
