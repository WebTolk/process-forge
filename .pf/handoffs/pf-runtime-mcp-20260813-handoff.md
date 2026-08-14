# Handoff: PF Runtime MCP Architecture

- date: 2026-08-13
- run: `pf-runtime-mcp-20260813`
- assignment: `runtime-mcp-architecture-report`
- status: architecture report completed; implementation not started

## Delivered

- Architecture report: `.pf/artifacts/pf-runtime-mcp-20260813/architecture-report.md`
- Log: `.pf/logs/pf-runtime-mcp-20260813.md`

## Main Decisions

- Keep PF Core and `.pf` files authoritative.
- Add Runtime as optional local interface/service only.
- Use loopback HTTP plus token for PoC IPC.
- Normalize external agent hook payloads into existing ProcessForge event envelopes.
- Expose MCP as a facade over existing context, state, path/resource, and event functions.
- Start with read-oriented MCP tools and event ingestion before command execution or network delivery.

## Current Blockers And Risks

- `project-context-check` reports a broken snapshot because required capabilities are missing and project classification changed.
- Codex and Kimi stable hook contracts were not confirmed from official docs in this pass.
- Existing event taxonomy may need deliberate extension before `agent.*` events validate under `process-event.schema.json`.

## Next Step

If the report is approved, create a separate PoC implementation assignment with narrow write scope for Runtime service code, adapter normalizer, projection builder, MCP facade, and focused tests.
