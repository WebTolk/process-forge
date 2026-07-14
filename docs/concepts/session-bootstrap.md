# Session Bootstrap

Session bootstrap turns a short launch request into a formal ProcessForge
session. The new default uses a project context snapshot instead of recompiling
every package, process, template, and Markdown note on each start.

## Session Start Request

A session starts from a structured request with:

- session id, mode, actor, and role
- project root
- optional assignment path
- options for writes, cache use, and context refresh

The request is represented by `schemas/session-start.schema.json` and
`templates/session-start-template.yaml`.

## Start Order

For `.pf` projects, read:

1. global agent instructions and the bounded ProcessForge section, if present
2. `.pf/AGENTS.md`
3. `.pf/process-forge.yaml`
4. `.pf/contexts/project-context.snapshot.md`
5. `.pf/contexts/project-context.snapshot.yaml` when machine-readable fields are needed
6. the current assignment
7. relevant recent status, log, review, handoff, and ADR files

Legacy root-layout projects use the same filenames without the `.pf/` prefix
until migration is reviewed.

## Modes

`resume` is used when an agent inspects an existing project flow and reports
current state. Default resume mode is report-only for public artifacts, while
private session telemetry is still written.

`project_init` starts Project Init. It creates `.pf/` by default and does not
create a root project `AGENTS.md`.

`assignment_execute` starts a worker for a bounded task. The worker receives an
assignment plus either an Execution Context Package or a snapshot-based context
capsule. It should not rediscover the whole project unless explicitly allowed.

`context_resolve`, `context_compile`, and `doctor_context` remain compatibility
modes for legacy context index workflows.

## Rules

- Prefer a fresh project context snapshot over broad context recomputation.
- If the snapshot is stale, report why and refresh when mode allows it.
- Do not silently continue when a required capability is missing.
- Treat assignment front matter or assignment YAML as machine authority.
- Treat Markdown body text as human-readable context.
- Write private session metadata and telemetry under `runtime/`.

The bootstrap layer is file-only. It does not require a backend, database,
dashboard, or mandatory runner.
