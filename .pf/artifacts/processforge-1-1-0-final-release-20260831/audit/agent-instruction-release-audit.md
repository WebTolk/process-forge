# Agent instruction release audit

Status: ready_for_review

## Blocking findings

1. The `START_AGENT_HERE.md` generator in `tools/processforge.py` still makes
   snapshot reading, active-assignment lookup, and `doctor-project` the first
   ordinary path, and advertises `hooks-dispatch`.
2. `templates/project-agents-template.md` tells agents to write runtime
   telemetry directly and starts from snapshot files rather than `pf.context`.
3. `docs/getting-started/agent-prompts.md` defines ordinary work through manual
   `session-start`, `agent-checkin`, context-check and low-level run/task CLI.
4. Generic project onboarding unconditionally installs `.codex/hooks.json`;
   missing hooks make `project-init-status` repairable.

## Required release contract

- Generated and repository-local entrypoints start from `.pf/AGENTS.md`, then
  `pf.context`, conditional `pf.search`, `pf.resolve`, and `pf.work.start`.
- Snapshot and file reading remain a fallback when MCP is unavailable.
- Infrastructure maintenance is operator work, not ordinary agent work.
- Codex hooks remain an explicit optional host integration and an informational
  status only.

## Files requiring synchronization

`tools/processforge.py`, `src/processforge_core/project_initialization.py`,
project-init smokes, `.pf/AGENTS.md`, `.pf/START_AGENT_HERE.md`, both agent
templates, agent prompt runbooks, and focused release invariant smokes.
