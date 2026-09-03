# Start Agent Here

You are working inside a ProcessForge-enabled project.

## Preferred Path

1. Read `.pf/AGENTS.md`.
2. Ask the ProcessForge MCP tool `pf.context` with this project root, or read `.pf/contexts/project-context.snapshot.yaml` when MCP is unavailable.
3. Use `pf.search` for project-authorized knowledge, template, process, and tool metadata before broader search.
4. Use `pf.resolve` for any resource id before opening local resource paths.
5. Perform local read-only analysis.
6. Use `pf.work.start` with a high-level objective when work becomes substantive.
7. Call `pf.work.state`; read the assignment and immutable capsule selected or
   created by PF.
8. Complete the current stage obligations and call `pf.work.transition` with
   an outcome and evidence. Do not provide a next stage.
9. Repeat until PF returns `action: run_completed`.

## Infrastructure Boundary

During ordinary project work, do not install, start, restart, or repair PF
Runtime, MCP, host hooks, or Agent Ledger. Use the available PF tools. If Forge
or a host integration is unavailable and PF returns an operator-level blocker,
report it concisely. Garage context, search, resolve, and work bootstrap do not
require Runtime, hooks, or a manual Ledger session.

Do not expose local absolute paths from `.pf/process-forge.local.yaml`. Do not
call a distribution-local CLI path from this project root unless this project
is the ProcessForge distribution itself.

## Current Work

Use `pf.context` and `pf.work.state` as the current source of truth. Do not use
the onboarding placeholder as an active assignment.

## Operator Diagnostics

Doctor, context refresh, hook dispatch, Runtime, Ledger, and search-index
maintenance commands are advanced/operator diagnostics, not the ordinary agent
start path.
