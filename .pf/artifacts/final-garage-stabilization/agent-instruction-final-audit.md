# Agent Instruction Final Audit

Date: 2026-08-24
Status: pass_with_changes_required

## Checked Surfaces

- `.pf/START_AGENT_HERE.md`
- `.pf/AGENTS.md`
- docs/concepts/runtime-mcp.md
- docs/concepts/garage-core.md
- docs/concepts/resource-search-index.md

## Current State

The project-local start file already points agents to:

1. `pf.context`;
2. `pf.search`;
3. `pf.resolve`;
4. local work;
5. governed work when substantive.

The remaining UX gap is that governed work still points to low-level
assignment/run commands. The preferred path must name `pf.work.start` so a
user-like prompt does not require the agent to know hook, Ledger, run-create,
task-create, or stage internals.

## Required Change

- Add `pf.work.start` to MCP.
- Update short agent-facing docs to mention it as the high-level transition into
  governed work.
- Keep low-level CLI/MCP commands as compatibility and diagnostic surface.
