# Agent Workflow Simplification Report

Date: 2026-09-02

Normal execution is now:

`pf.context -> pf.work.start(objective) -> pf.work.state -> pf.work.transition(outcome, evidence, notes)`.

The agent neither selects a next stage nor creates a Run or Assignment in the normal path. `pf.work.start` selects `initial_stage` or the first executable stage. The public MCP contract rejects `preferred_stage`; it is not a hidden bypass.

Updated guidance: `.pf/AGENTS.md`, `.pf/START_AGENT_HERE.md`, `templates/project-agents-template.md`, `templates/process-agent-prompt.md`, `docs/concepts/garage-core.md`, `docs/concepts/runtime-mcp.md`, and the new English/Russian declarative execution concepts.

The legacy `pf.work_state` MCP shape remains a compatibility alias. The declarative API is `pf.work.state`.
