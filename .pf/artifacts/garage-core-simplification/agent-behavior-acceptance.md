# Agent Behavior Acceptance

Date: 2026-08-24
Status: pass_with_conditions

Verified behavior:

- `.pf/START_AGENT_HERE.md` now tells a fresh agent to begin with `pf.context`,
  then `pf.search`, then `pf.resolve`, before governed work.
- Direct MCP stdio call to `pf.context` on `<project-root>` without
  `--session` returned `mode: garage`, fresh context, and `search_status:
  ready`.
- Direct MCP stdio call to `pf.search` on the same project without `--session`
  returned the project-local resource
  `project.process-forge:project-profile`.

Condition:

- This is local stdio MCP proof. A hosted Codex MCP transcript from a newly
  opened UI session was not produced in this run and must not be claimed as
  complete hosted-session acceptance.
