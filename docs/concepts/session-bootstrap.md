# Session Bootstrap

Session bootstrap turns a short launch request into a formal ProcessForge session.
The goal is to decide how the agent should start, which sources it may read, and
whether context must be rebuilt before work begins.

## Session Start Request

A session starts from a structured request with:

- session id, mode, actor, and role
- project root or ProcessForge root
- optional assignment path
- options for writes, cache use, and context rebuilds

The request is represented by `schemas/session-start.schema.json` and
`templates/session-start-template.yaml`.

## Modes

`resume` is used when an agent is asked to inspect an existing project flow and
report current state. It reads the project `AGENTS.md`, `process-forge.yaml`,
optional local config, context files, assignments, artifacts, reviews, logs,
handoffs, and ADRs. In report-only mode it writes nothing.

`project_init` is a session protocol for starting Project Init. It delegates the
actual project-layer creation to the Project Init model and keeps the same safety
rules: dry-run first, no local absolute paths in public files, and no overwrite
without explicit approval.

`assignment_execute` is used when an orchestrator or runner starts a worker for a
bounded task. The worker receives an assignment plus an Execution Context Package
and, optionally, a context capsule. It should not rediscover the whole project
unless that is explicitly allowed.

`context_resolve`, `context_compile`, and `doctor_context` are operational modes
used by tooling to resolve inputs, build worker context, and verify freshness.

## Bootloader Principle

The global `AGENTS.md` should stay small. It should tell an agent how to find the
workplace manifest, project flow, session mode, context resolver, registries, and
conflict policy. It should not become the knowledge base itself.

## Startup Flow

1. Parse the short launch request into a Session Start Request.
2. Detect the session mode.
3. Locate the project flow and workplace layer.
4. Check context freshness.
5. Reuse fresh context or rebuild only when allowed.
6. Produce a status report, context index, or execution context depending on mode.

The bootstrap layer is file-only. It does not require a backend, database,
dashboard, or runner.
